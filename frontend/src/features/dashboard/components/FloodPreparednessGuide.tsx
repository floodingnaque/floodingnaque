/**
 * FloodPreparednessGuide
 *
 * Phase-based preparedness guide (Before / During / After) with
 * accordion items, search filter, and emergency contacts grid.
 * Auto-selects phase based on current risk from useLivePrediction().
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EMERGENCY_CONTACTS } from "@/config/paranaque";
import { useLivePrediction } from "@/features/flooding/hooks/useLivePrediction";
import { cn } from "@/lib/utils";
import {
  Ban,
  Brain,
  ChevronDown,
  ClipboardList,
  FileText,
  HeartPulse,
  Home,
  MapPin,
  PersonStanding,
  Phone,
  Radio,
  Search,
  ShieldCheck,
  Siren,
  Smartphone,
  Sparkles,
  Sun,
  Users,
  Waves,
  Wrench,
  Zap,
} from "lucide-react";
import { memo, useCallback, useMemo, useState } from "react";
import type { PreparednessItem, PreparednessPhase } from "../types";

// ---------------------------------------------------------------------------
// Static preparedness data
// ---------------------------------------------------------------------------

const PHASES: PreparednessPhase[] = [
  {
    icon: ShieldCheck,
    label: "Before",
    color: "text-risk-safe border-risk-safe/40 bg-risk-safe/10",
    items: [
      {
        icon: ClipboardList,
        title: "Prepare go-bags",
        desc: "Pack water, food, medicine, documents, flashlight, phone charger, and first-aid kit for each family member.",
      },
      {
        icon: MapPin,
        title: "Know your evacuation route",
        desc: "Identify the nearest evacuation center and practice the route with your household.",
      },
      {
        icon: Radio,
        title: "Monitor official channels",
        desc: "Follow PAGASA bulletins, DRRMO announcements, and Parañaque City social media for early warnings.",
      },
      {
        icon: Wrench,
        title: "Secure your home",
        desc: "Clear drainage, elevate appliances, and reinforce doors and windows before the wet season.",
      },
      {
        icon: Users,
        title: "Coordinate with neighbors",
        desc: "Establish a buddy system, especially for elderly, PWD, and solo-parent households.",
      },
    ],
  },
  {
    icon: Waves,
    label: "During",
    color: "text-risk-alert border-risk-alert/40 bg-risk-alert/10",
    items: [
      {
        icon: PersonStanding,
        title: "Evacuate early",
        desc: "Do not wait for chest-high water. Move to higher ground or the nearest evacuation center immediately.",
      },
      {
        icon: Zap,
        title: "Turn off utilities",
        desc: "Switch off electricity at the main breaker and gas valves before evacuating.",
      },
      {
        icon: Ban,
        title: "Avoid floodwater contact",
        desc: "Floodwater carries sewage, chemicals, and sharp debris. Never wade through moving water.",
      },
      {
        icon: Smartphone,
        title: "Stay connected",
        desc: "Keep your phone charged. Text — don't call — to keep lines free. Notify relatives of your status.",
      },
      {
        icon: Siren,
        title: "Signal for help",
        desc: "If trapped, move to the highest point, wave a cloth or flashlight, and call 911 / 8888.",
      },
    ],
  },
  {
    icon: Sun,
    label: "After",
    color: "text-blue-400 border-blue-400/40 bg-blue-400/10",
    items: [
      {
        icon: Home,
        title: "Return cautiously",
        desc: "Only go home when authorities declare it safe. Check for structural damage before entering.",
      },
      {
        icon: Sparkles,
        title: "Clean and disinfect",
        desc: "Hose down walls, mop with bleach solution, and discard contaminated food and medicine.",
      },
      {
        icon: HeartPulse,
        title: "Watch for illness",
        desc: "Leptospirosis, dengue, and skin infections are common post-flood. Seek medical attention for fever or wounds.",
      },
      {
        icon: FileText,
        title: "Document & report damage",
        desc: "Take photos of property damage and report to your barangay for relief eligibility.",
      },
      {
        icon: Brain,
        title: "Mental health check",
        desc: "Flooding is traumatic. Check in on children/elders. Call Hopeline 8804-4673 for support.",
      },
    ],
  },
];

const CONTACTS_LIST = Object.values(EMERGENCY_CONTACTS);

// ---------------------------------------------------------------------------
// Accordion item
// ---------------------------------------------------------------------------

function GuideItem({
  item,
  isOpen,
  onToggle,
}: {
  item: PreparednessItem;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const Icon = item.icon;
  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between py-2.5 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="text-[11px] font-mono font-medium text-foreground truncate">
            {item.title}
          </span>
        </div>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 text-muted-foreground shrink-0 transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </button>
      {isOpen && (
        <div className="pb-3 pl-8 pr-2">
          <p className="text-[11px] font-mono text-muted-foreground leading-relaxed">
            {item.desc}
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const FloodPreparednessGuide = memo(function FloodPreparednessGuide() {
  const [openItems, setOpenItems] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState("");
  const { data: prediction } = useLivePrediction();

  const autoPhase = prediction
    ? prediction.risk_label === "Critical"
      ? 1
      : prediction.risk_label === "Alert"
        ? 0
        : 2
    : 0;
  const [manualPhase, setManualPhase] = useState<number | null>(null);
  const activePhase = manualPhase ?? autoPhase;

  const toggleItem = useCallback((key: string) => {
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const phase = PHASES[activePhase]!;

  const filteredItems = useMemo(() => {
    if (!search.trim()) return phase.items;
    const q = search.toLowerCase();
    return phase.items.filter(
      (it) =>
        it.title.toLowerCase().includes(q) || it.desc.toLowerCase().includes(q),
    );
  }, [phase.items, search]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <CardTitle className="flex items-center gap-2 text-sm font-bold font-mono tracking-wide">
          <ShieldCheck className="h-4 w-4" />
          Flood Preparedness Guide
        </CardTitle>
        {prediction && (
          <Badge
            variant="outline"
            className={cn(
              "text-[9px] font-mono px-1.5 py-0",
              prediction.risk_label === "Critical"
                ? "text-risk-critical border-risk-critical/40"
                : prediction.risk_label === "Alert"
                  ? "text-risk-alert border-risk-alert/40"
                  : "text-risk-safe border-risk-safe/40",
            )}
          >
            {prediction.risk_label} — auto-phase
          </Badge>
        )}
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Phase selector */}
        <div className="flex gap-1">
          {PHASES.map((p, i) => (
            <button
              key={p.label}
              type="button"
              onClick={() => setManualPhase(i)}
              className={cn(
                "flex-1 rounded-md border px-2 py-1.5 text-[10px] font-mono transition-colors text-center",
                activePhase === i
                  ? p.color
                  : "text-muted-foreground border-border bg-muted hover:bg-accent/50",
              )}
            >
              <p.icon className="h-3.5 w-3.5 inline-block mr-1 align-text-bottom" />
              {p.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tips…"
            className="w-full rounded-md border border-border bg-muted pl-8 pr-3 py-1.5 text-[11px] font-mono text-foreground placeholder:text-muted-foreground outline-none"
          />
        </div>

        {/* Accordion */}
        <div>
          {filteredItems.length === 0 ? (
            <div className="py-4 text-center text-xs text-muted-foreground font-mono">
              No matching tips.
            </div>
          ) : (
            filteredItems.map((item) => {
              const key = `${phase.label}-${item.title}`;
              return (
                <GuideItem
                  key={key}
                  item={item}
                  isOpen={openItems.has(key)}
                  onToggle={() => toggleItem(key)}
                />
              );
            })
          )}
        </div>

        {/* Emergency contacts */}
        <div className="border-t border-border pt-3">
          <div className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-mono mb-2">
            Emergency Hotlines
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            {CONTACTS_LIST.map((c) => (
              <div
                key={c.name}
                className="flex items-start gap-2 rounded-md border border-border bg-muted p-2"
              >
                <Phone className="h-3 w-3 text-muted-foreground mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <div className="text-[10px] font-mono font-medium text-foreground truncate">
                    {c.name}
                  </div>
                  <div className="text-[10px] font-mono text-primary">
                    {c.phone}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

export function FloodPreparednessGuideSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-52" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-1">
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="h-8 flex-1" />
        </div>
        <Skeleton className="h-8 w-full" />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
        <Skeleton className="h-32 w-full" />
      </CardContent>
    </Card>
  );
}
