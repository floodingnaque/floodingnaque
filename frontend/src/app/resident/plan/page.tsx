/**
 * Resident — Evacuation Plan Page
 */

import { MapPin, Route } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ResidentPlanPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Route className="h-4 w-4 text-primary" />
            My Evacuation Plan
          </CardTitle>
          <CardDescription>
            Plan your route to the nearest evacuation center
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Map placeholder */}
          <div className="w-full aspect-video bg-muted/50 rounded-lg flex flex-col items-center justify-center text-muted-foreground mb-4">
            <MapPin className="h-10 w-10 mb-2 opacity-30" />
            <p className="text-sm font-medium">Evacuation Route Map</p>
            <p className="text-xs mt-1">
              Shows your location & the best route to the nearest center
            </p>
          </div>

          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium text-foreground">
                Step 1: Know Your Meeting Point
              </p>
              <p className="mt-1">
                Agree with your household on a meeting point outside your home
                in case you get separated.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium text-foreground">
                Step 2: Identify Your Route
              </p>
              <p className="mt-1">
                Choose the shortest safe route to the nearest evacuation center.
                Avoid flood-prone roads.
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/50">
              <p className="font-medium text-foreground">
                Step 3: Practice the Route
              </p>
              <p className="mt-1">
                Walk your evacuation route with your family so everyone knows
                the way, even in the dark.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
