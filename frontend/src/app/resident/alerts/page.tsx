/**
 * Resident — Active Alerts Page
 */

import { Bell, ShieldCheck } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";

export default function ResidentAlertsPage() {
  const { data: prediction, isLoading } = useLivePrediction();

  const alert = prediction?.smart_alert;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-primary" />
            Active Alerts
          </CardTitle>
          <CardDescription>
            Real-time flood warnings and safety notifications
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : alert && !alert.was_suppressed ? (
            <div className="space-y-3">
              <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <div className="flex items-start gap-3">
                  <Bell className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-amber-700">
                      Flood Alert — {alert.escalation_state}
                    </p>
                    <p className="text-xs text-amber-600 mt-1">
                      3-hour rainfall: {alert.rainfall_3h} mm
                    </p>
                    {alert.contributing_factors.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {alert.contributing_factors.map((f, i) => (
                          <p key={i} className="text-xs text-amber-600">
                            • {f}
                          </p>
                        ))}
                      </div>
                    )}
                    {alert.escalation_reason && (
                      <p className="text-xs text-amber-600 mt-1">
                        Reason: {alert.escalation_reason}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <ShieldCheck className="h-10 w-10 mb-3 text-green-500 opacity-60" />
              <p className="text-sm font-medium">All Clear</p>
              <p className="text-xs mt-1">
                No active flood alerts for your area
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tips */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">When You Receive an Alert</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            1. Stay calm and monitor updates from this app and official
            channels.
          </p>
          <p>2. Prepare your emergency go-bag if risk escalates.</p>
          <p>3. Follow evacuation instructions from your barangay or MDRRMO.</p>
          <p>4. Move to higher ground if flooding begins in your area.</p>
          <p>5. Call the emergency hotlines listed in Emergency Contacts.</p>
        </CardContent>
      </Card>
    </div>
  );
}
