/**
 * Resident — Nearby Evacuation Centers Page
 */

import { Building, MapPin, Navigation, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface EvacCenter {
  name: string;
  barangay: string;
  capacity: number;
  status: "open" | "standby" | "closed";
  address: string;
}

const CENTERS: EvacCenter[] = [
  {
    name: "Parañaque National High School",
    barangay: "San Antonio",
    capacity: 500,
    status: "standby",
    address: "San Antonio, Parañaque City",
  },
  {
    name: "Barangay Hall - BF Homes",
    barangay: "BF Homes",
    capacity: 200,
    status: "standby",
    address: "BF Homes, Parañaque City",
  },
  {
    name: "Dr. Arcadio Santos National High School",
    barangay: "La Huerta",
    capacity: 800,
    status: "standby",
    address: "La Huerta, Parañaque City",
  },
];

function statusColor(status: EvacCenter["status"]) {
  switch (status) {
    case "open":
      return "bg-green-500/10 text-green-700 border-green-500/30";
    case "standby":
      return "bg-amber-500/10 text-amber-700 border-amber-500/30";
    case "closed":
      return "bg-muted text-muted-foreground border-border";
  }
}

export default function ResidentEvacuationPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Building className="h-4 w-4 text-primary" />
            Nearby Evacuation Centers
          </CardTitle>
          <CardDescription>
            Go to the nearest open center if instructed to evacuate
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {CENTERS.map((center) => (
            <div
              key={center.name}
              className="flex items-start gap-4 p-4 rounded-lg border border-border/50"
            >
              <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                <Building className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-medium">{center.name}</p>
                  <Badge
                    variant="outline"
                    className={statusColor(center.status)}
                  >
                    {center.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {center.address}
                </p>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Users className="h-3 w-3" />
                    Capacity: {center.capacity}
                  </span>
                  <span className="flex items-center gap-1">
                    <Navigation className="h-3 w-3" />
                    Get Directions
                  </span>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Tips */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evacuation Reminders</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            1. Bring your emergency go-bag (documents, medicine, water,
            clothes).
          </p>
          <p>2. Turn off electricity and gas before leaving your home.</p>
          <p>
            3. Avoid walking through floodwaters — they may be deeper than they
            appear.
          </p>
          <p>4. Register at the evacuation center upon arrival.</p>
          <p>5. Stay at the center until officials say it is safe to return.</p>
        </CardContent>
      </Card>
    </div>
  );
}
