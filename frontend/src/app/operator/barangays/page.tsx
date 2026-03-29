/**
 * Operator - Barangays Overview Page (Read-only)
 *
 * Displays all 16 Parañaque barangays with flood risk status,
 * population, zone, and evacuation center info. Operators use this
 * for situational awareness - admin handles edits.
 */

import { Breadcrumb } from "@/components/layout/Breadcrumb";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { Badge } from "@/components/ui/badge";
import { GlassCard } from "@/components/ui/glass-card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { BARANGAYS, type BarangayData } from "@/config/paranaque";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  CheckCircle,
  Landmark,
  Search,
  Shield,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";

// ── Risk styling ─────────────────────────────────────────────────

type FloodRisk = BarangayData["floodRisk"];

const RISK_BADGE: Record<FloodRisk, string> = {
  high: "bg-risk-critical/10 text-risk-critical border-risk-critical/30",
  moderate: "bg-risk-alert/10 text-risk-alert border-risk-alert/30",
  low: "bg-risk-safe/10 text-risk-safe border-risk-safe/30",
};

const RISK_ICON: Record<FloodRisk, React.ElementType> = {
  high: AlertTriangle,
  moderate: Shield,
  low: CheckCircle,
};

// ── Component ────────────────────────────────────────────────────

export default function OperatorBarangaysPage() {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return BARANGAYS;
    return BARANGAYS.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.zone.toLowerCase().includes(q) ||
        b.evacuationCenter.toLowerCase().includes(q),
    );
  }, [search]);

  const riskCounts = useMemo(() => {
    const counts: Record<FloodRisk, number> = { high: 0, moderate: 0, low: 0 };
    for (const b of BARANGAYS) counts[b.floodRisk]++;
    return counts;
  }, []);

  const totalPop = useMemo(
    () => BARANGAYS.reduce((sum, b) => sum + b.population, 0),
    [],
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="container mx-auto max-w-6xl px-4 pt-6">
        <Breadcrumb
          items={[
            { label: "Operations", href: "/operator" },
            { label: "Barangays" },
          ]}
          className="mb-4"
        />
      </div>

      {/* Summary stats */}
      <section className="py-8 bg-muted/30">
        <div className="container mx-auto max-w-6xl px-4">
          <SectionHeading
            label="Summary"
            title="Risk Distribution"
            subtitle="Current flood risk classification per DRRMO records (2022–2025)"
          />
          <div className="grid gap-4 sm:grid-cols-4 mt-6">
            <GlassCard intensity="light" className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Landmark className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{BARANGAYS.length}</p>
                  <p className="text-xs text-muted-foreground">
                    Total Barangays
                  </p>
                </div>
              </div>
            </GlassCard>

            <GlassCard intensity="light" className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-risk-critical/10 flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5 text-risk-critical" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{riskCounts.high}</p>
                  <p className="text-xs text-muted-foreground">High Risk</p>
                </div>
              </div>
            </GlassCard>

            <GlassCard intensity="light" className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-risk-alert/10 flex items-center justify-center">
                  <Shield className="h-5 w-5 text-risk-alert" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{riskCounts.moderate}</p>
                  <p className="text-xs text-muted-foreground">Moderate Risk</p>
                </div>
              </div>
            </GlassCard>

            <GlassCard intensity="light" className="p-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center">
                  <Users className="h-5 w-5 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {(totalPop / 1000).toFixed(0)}k
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Total Population
                  </p>
                </div>
              </div>
            </GlassCard>
          </div>
        </div>
      </section>

      {/* Table section */}
      <section className="py-8 bg-background">
        <div className="container mx-auto max-w-6xl px-4">
          <SectionHeading
            label="Directory"
            title="All Barangays"
            subtitle="Search by name, zone, or evacuation center"
          />

          {/* Search */}
          <div className="mt-6 mb-4 max-w-sm">
            <div className="relative flex items-center rounded-xl border border-border/50 bg-background/50 backdrop-blur-sm focus-within:ring-2 focus-within:ring-primary/30">
              <div className="pointer-events-none pl-3.5 text-muted-foreground/60">
                <Search className="h-4 w-4" />
              </div>
              <Input
                placeholder="Search barangays…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="border-0 bg-transparent focus-visible:ring-0 pl-2"
              />
            </div>
          </div>

          <GlassCard intensity="medium" className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Barangay</TableHead>
                  <TableHead>Zone</TableHead>
                  <TableHead>Flood Risk</TableHead>
                  <TableHead className="text-right">Population</TableHead>
                  <TableHead className="text-right">Area (km²)</TableHead>
                  <TableHead className="text-right">Flood Events</TableHead>
                  <TableHead>Evacuation Center</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={7}
                      className="text-center text-muted-foreground py-8"
                    >
                      No barangays match your search.
                    </TableCell>
                  </TableRow>
                ) : (
                  filtered.map((b) => {
                    const Icon = RISK_ICON[b.floodRisk];
                    return (
                      <TableRow key={b.key}>
                        <TableCell className="font-medium">{b.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">
                            {b.zone}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs capitalize gap-1",
                              RISK_BADGE[b.floodRisk],
                            )}
                          >
                            <Icon className="h-3 w-3" />
                            {b.floodRisk}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {b.population.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {b.area.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {b.floodEvents}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {b.evacuationCenter}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </GlassCard>
        </div>
      </section>
    </div>
  );
}
