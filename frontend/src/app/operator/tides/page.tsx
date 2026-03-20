/**
 * Operator — Tidal & River Level Monitoring Page
 */

import { Ruler, TrendingDown, TrendingUp, Waves } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function OperatorTidesPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Current Levels */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
              <Waves className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xl font-bold">—</p>
              <p className="text-xs text-muted-foreground">Tidal Level</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-cyan-500/10 flex items-center justify-center shrink-0">
              <Ruler className="h-5 w-5 text-cyan-500" />
            </div>
            <div>
              <p className="text-xl font-bold">—</p>
              <p className="text-xs text-muted-foreground">River Level</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-green-500/10 flex items-center justify-center shrink-0">
              <TrendingDown className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="text-xl font-bold">—</p>
              <p className="text-xs text-muted-foreground">Next Low Tide</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
              <TrendingUp className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <p className="text-xl font-bold">—</p>
              <p className="text-xs text-muted-foreground">Next High Tide</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tidal Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Waves className="h-4 w-4 text-primary" />
            Tidal Schedule
          </CardTitle>
          <CardDescription>
            24-hour tidal predictions for Manila Bay / Parañaque coastline
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/50 rounded-lg">
            <Waves className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">Tidal Chart Coming Soon</p>
            <p className="text-xs mt-1">
              Will integrate with PAGASA tidal data and NAMRIA water level
              stations
            </p>
          </div>
        </CardContent>
      </Card>

      {/* River Monitoring */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Ruler className="h-4 w-4 text-primary" />
            River & Waterway Monitoring
          </CardTitle>
          <CardDescription>
            Water level sensors along major drainage channels
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground border border-dashed border-border/50 rounded-lg">
            <Ruler className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">Sensor Integration Pending</p>
            <p className="text-xs mt-1">
              IoT water level sensors will report here once connected
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
