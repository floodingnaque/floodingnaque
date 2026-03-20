/**
 * Resident — Report Flood Page
 */

import { AlertTriangle, Camera, MapPin, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function ResidentReportPage() {
  const [severity, setSeverity] = useState("moderate");

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            Report Flooding
          </CardTitle>
          <CardDescription>
            Help your community by reporting flood conditions in your area. Your
            report will be verified by MDRRMO operators.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Location */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Location</p>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                className="pl-10"
                placeholder="Street, barangay, or landmark…"
              />
            </div>
          </div>

          {/* Severity */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Flood Severity</p>
            <Select value={severity} onValueChange={setSeverity}>
              <SelectTrigger>
                <SelectValue placeholder="Select severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="minor">
                  Minor — ankle-deep, passable
                </SelectItem>
                <SelectItem value="moderate">
                  Moderate — knee-deep, difficult to walk
                </SelectItem>
                <SelectItem value="severe">
                  Severe — waist-deep or higher, impassable
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Water Level */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Estimated Water Level</p>
            <Input placeholder="e.g., 30 cm, knee-deep" />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Description</p>
            <textarea
              className="w-full min-h-24 p-3 rounded-lg border border-border/50 bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Describe the flood situation — how fast is water rising? Are people stranded? Is the road passable?"
            />
          </div>

          {/* Photo */}
          <div className="space-y-1.5">
            <p className="text-sm font-medium">Photo (Optional)</p>
            <div className="flex items-center gap-3">
              <Button variant="outline" className="gap-2">
                <Camera className="h-4 w-4" />
                Take Photo
              </Button>
              <p className="text-xs text-muted-foreground">
                Attach a photo to help operators verify the report
              </p>
            </div>
          </div>

          {/* Submit */}
          <Button className="w-full gap-2">
            <Send className="h-4 w-4" />
            Submit Report
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
