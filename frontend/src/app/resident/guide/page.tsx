/**
 * Resident — Flood Safety Guide Page
 */

import {
  BookOpen,
  CheckCircle,
  CloudRain,
  Home,
  ShieldCheck,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ResidentGuidePage() {
  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-2xl mx-auto pb-24 md:pb-6">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          Flood Safety Guide
        </h2>
        <p className="text-sm text-muted-foreground">
          Essential tips for before, during, and after a flood
        </p>
      </div>

      {/* Before */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-green-600" />
            Before a Flood
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          {[
            "Know your barangay's flood-prone areas and evacuation routes.",
            "Prepare an emergency go-bag with documents, medicine, water, and clothes.",
            "Elevate appliances and important items above expected flood levels.",
            "Keep your phone charged and emergency numbers saved.",
            "Install the Floodingnaque app and enable push notifications.",
            "Check for PAGASA weather advisories daily during rainy season.",
          ].map((tip, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
              <p>{tip}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* During */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <CloudRain className="h-4 w-4 text-amber-600" />
            During a Flood
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          {[
            "Move to higher ground immediately if water is rising.",
            "Do NOT walk, swim, or drive through floodwaters. Turn around.",
            "Stay away from downed power lines and electrical wires.",
            "If trapped, go to the highest point and signal for help.",
            "Listen to official advisories — follow MDRRMO instructions.",
            "Keep children and elderly supervised at all times.",
          ].map((tip, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
              <p>{tip}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* After */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Home className="h-4 w-4 text-blue-600" />
            After a Flood
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          {[
            "Return home only when authorities say it is safe.",
            "Check for structural damage before entering your house.",
            "Avoid contact with floodwater — it may be contaminated.",
            "Clean and disinfect everything that got wet.",
            "Document damage with photos for insurance or assistance claims.",
            "Boil water or use bottled water until supply is confirmed safe.",
          ].map((tip, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
              <p>{tip}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
