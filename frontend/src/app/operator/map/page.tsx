/**
 * Operator — Live Flood Map Page
 */

import { Layers, MapPin, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { RISK_CONFIGS, type RiskLevel } from "@/types/api/prediction";

const RISK_BADGE: Record<RiskLevel, string> = {
  0: "bg-green-500/10 text-green-700 border-green-500/30",
  1: "bg-amber-500/10 text-amber-700 border-amber-500/30",
  2: "bg-red-500/10 text-red-700 border-red-500/30",
};

export default function OperatorMapPage() {
  const { data: prediction, isLoading, refetch } = useLivePrediction();
  const riskLevel = (prediction?.risk_level ?? 0) as RiskLevel;

  return (
    <div className="p-4 sm:p-6 space-y-4">
      {/* Map controls bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Layers className="h-3 w-3" />
            Flood Risk Overlay
          </Badge>
          {prediction && (
            <Badge variant="outline" className={RISK_BADGE[riskLevel]}>
              {RISK_CONFIGS[riskLevel].label}
            </Badge>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </Button>
      </div>

      {/* Map placeholder */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <Skeleton className="w-full aspect-video" />
          ) : (
            <div className="w-full aspect-video bg-muted/50 flex flex-col items-center justify-center text-muted-foreground">
              <MapPin className="h-12 w-12 mb-3 opacity-30" />
              <p className="text-sm font-medium">Interactive Map</p>
              <p className="text-xs mt-1">
                Leaflet integration will render here
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Center: 14.4793°N, 121.0198°E (Parañaque City)
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Legend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-green-500" />
              Safe
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-amber-500" />
              Alert
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-red-500" />
              Critical
            </div>
            <div className="flex items-center gap-2">
              <span className="h-3 w-3 rounded-full bg-blue-500" />
              Evacuation Center
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
