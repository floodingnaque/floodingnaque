/**
 * Operator — Alert Management Page
 */

import { Bell, Filter, Search, ShieldCheck } from "lucide-react";
import { useState } from "react";

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

export default function OperatorAlertsPage() {
  const [search, setSearch] = useState("");

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search alerts by barangay or ID..."
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1">
            <Filter className="h-3.5 w-3.5" />
            Filters
          </Button>
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
              </CardTitle>
              <CardDescription>
                All active and historical alerts
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">
              Real-time via SSE
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <ShieldCheck className="h-12 w-12 mb-3 text-emerald-500/50" />
            <p className="text-base font-medium">No Active Alerts</p>
            <p className="text-sm mt-1">
              All alerts have been acknowledged and resolved.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Smart Alert Evaluator Status */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Smart Alert Evaluator</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground text-xs">Last Evaluation</p>
              <p className="font-medium">—</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Next Scheduled</p>
              <p className="font-medium">—</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Suppression State</p>
              <Badge variant="outline" className="text-xs mt-0.5">
                Inactive
              </Badge>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">
                False Alarm Filter
              </p>
              <Badge variant="secondary" className="text-xs mt-0.5">
                Enabled
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
