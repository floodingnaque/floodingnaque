/**
 * Operator — Analytics & Trends Page
 */

import { BarChart3, Calendar, TrendingUp } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function OperatorAnalyticsPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Overview cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">0</p>
            <p className="text-xs text-muted-foreground">Incidents (30d)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">—</p>
            <p className="text-xs text-muted-foreground">Avg Response Time</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">0</p>
            <p className="text-xs text-muted-foreground">Evacuees (30d)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-2xl font-bold">—</p>
            <p className="text-xs text-muted-foreground">Prediction Accuracy</p>
          </CardContent>
        </Card>
      </div>

      {/* Chart Placeholder - Incident Trends */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Incident Trends
          </CardTitle>
          <CardDescription>Monthly flood incidents over time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/50 rounded-lg">
            <BarChart3 className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">Chart Coming Soon</p>
            <p className="text-xs mt-1">
              Incident data will populate over time
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Risk Heatmap Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Calendar className="h-4 w-4 text-primary" />
            Seasonal Risk Patterns
          </CardTitle>
          <CardDescription>
            Historical flood risk by month and barangay
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/50 rounded-lg">
            <Calendar className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">Heatmap Coming Soon</p>
            <p className="text-xs mt-1">
              Seasonal patterns will appear after sufficient data collection
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
