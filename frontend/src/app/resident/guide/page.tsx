/**
 * Resident — Flood Safety Guide Page
 *
 * Interactive tick-off checklists for Before/During/After flood
 * and Go-Bag checklist with progress saved to localStorage.
 */

import {
  Backpack,
  BookOpen,
  CheckCircle,
  CloudRain,
  Home,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STORAGE_KEY = "floodingnaque_guide_checked";

interface ChecklistSection {
  id: string;
  title: string;
  titleFil: string;
  icon: React.ElementType;
  iconColor: string;
  items: { en: string; fil: string }[];
}

const CHECKLISTS: ChecklistSection[] = [
  {
    id: "before",
    title: "Before a Flood",
    titleFil: "Bago Mag-baha",
    icon: ShieldCheck,
    iconColor: "text-green-600",
    items: [
      {
        en: "Know your barangay's flood-prone areas and evacuation routes.",
        fil: "Alamin ang mga lugar na prone sa baha at ruta ng paglikas.",
      },
      {
        en: "Prepare an emergency go-bag with documents, medicine, water, and clothes.",
        fil: "Mag-ready ng go-bag may dokumento, gamot, tubig, at damit.",
      },
      {
        en: "Elevate appliances and important items above expected flood levels.",
        fil: "Itaas ang mga appliances at mahahalagang gamit.",
      },
      {
        en: "Keep your phone charged and emergency numbers saved.",
        fil: "Siguraduhing naka-charge ang phone at naka-save ang mga emergency number.",
      },
      {
        en: "Enable push notifications from Floodingnaque.",
        fil: "I-enable ang notifications mula sa Floodingnaque.",
      },
      {
        en: "Check PAGASA weather advisories daily during rainy season.",
        fil: "Araw-araw na i-check ang advisory ng PAGASA tuwing tag-ulan.",
      },
    ],
  },
  {
    id: "during",
    title: "During a Flood",
    titleFil: "Habang Bumabaha",
    icon: CloudRain,
    iconColor: "text-amber-600",
    items: [
      {
        en: "Move to higher ground immediately if water is rising.",
        fil: "Pumunta agad sa mataas na lugar kapag tumataas ang tubig.",
      },
      {
        en: "Do NOT walk, swim, or drive through floodwaters. Turn around.",
        fil: "HUWAG lumakad, lumangoy, o mag-drive sa baha. Bumalik.",
      },
      {
        en: "Stay away from downed power lines and electrical wires.",
        fil: "Lumayo sa bumagsak na mga linya ng kuryente.",
      },
      {
        en: "If trapped, go to the highest point and signal for help.",
        fil: "Kapag na-trap, pumunta sa pinakamataas at mag-signal ng tulong.",
      },
      {
        en: "Listen to official advisories — follow MDRRMO instructions.",
        fil: "Sumunod sa mga opisyal na advisory at MDRRMO.",
      },
      {
        en: "Keep children and elderly supervised at all times.",
        fil: "Bantayan ang mga bata at matatanda sa lahat ng oras.",
      },
    ],
  },
  {
    id: "after",
    title: "After a Flood",
    titleFil: "Pagkatapos ng Baha",
    icon: Home,
    iconColor: "text-blue-600",
    items: [
      {
        en: "Return home only when authorities say it is safe.",
        fil: "Umuwi lang kapag sinabi ng mga opisyal na ligtas na.",
      },
      {
        en: "Check for structural damage before entering your house.",
        fil: "Suriin ang sira sa bahay bago pumasok.",
      },
      {
        en: "Avoid contact with floodwater — it may be contaminated.",
        fil: "Iwasan ang pagdikit sa baha — maaaring kontaminado ito.",
      },
      {
        en: "Clean and disinfect everything that got wet.",
        fil: "Linisin at i-disinfect ang lahat ng nabasa.",
      },
      {
        en: "Document damage with photos for insurance or assistance.",
        fil: "Kuhanan ng litrato ang mga nasira para sa insurance o tulong.",
      },
      {
        en: "Boil water or use bottled water until supply is safe.",
        fil: "Magpakulo ng tubig o gumamit ng bottled water.",
      },
    ],
  },
  {
    id: "gobag",
    title: "Go-Bag Checklist",
    titleFil: "Checklist ng Go-Bag",
    icon: Backpack,
    iconColor: "text-purple-600",
    items: [
      {
        en: "IDs and important documents (in waterproof bag)",
        fil: "ID at mahahalagang dokumento (sa waterproof bag)",
      },
      {
        en: "Prescription medicines and first aid kit",
        fil: "Mga gamot at first aid kit",
      },
      {
        en: "Drinking water (at least 1 liter per person)",
        fil: "Inuming tubig (1 litro bawat tao)",
      },
      {
        en: "Non-perishable food and can opener",
        fil: "Pagkaing hindi nasisira at can opener",
      },
      { en: "Extra clothes and blanket", fil: "Ekstrang damit at kumot" },
      {
        en: "Phone charger / power bank",
        fil: "Charger ng phone / power bank",
      },
      {
        en: "Flashlight and extra batteries",
        fil: "Flashlight at ekstra baterya",
      },
      { en: "Cash (small bills)", fil: "Cash (maliliit na denomination)" },
      {
        en: "Whistle (to signal for help)",
        fil: "Whistle (para tumawag ng tulong)",
      },
      {
        en: "Face mask and hand sanitizer",
        fil: "Face mask at hand sanitizer",
      },
    ],
  },
];

export default function ResidentGuidePage() {
  const [checked, setChecked] = useState<Record<string, boolean>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {
      /* ignore */
    }
    return {};
  });

  const toggle = useCallback((key: string) => {
    setChecked((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 w-full">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          Gabay sa Kaligtasan / Flood Safety Guide
        </h2>
        <p className="text-sm text-muted-foreground">
          Interactive checklist — tap items to mark them done
        </p>
      </div>

      {CHECKLISTS.map((section) => {
        const SectionIcon = section.icon;
        const totalItems = section.items.length;
        const doneCount = section.items.filter(
          (_, i) => checked[`${section.id}-${i}`],
        ).length;
        const allDone = doneCount === totalItems;

        return (
          <Card key={section.id}>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <SectionIcon className={`h-4 w-4 ${section.iconColor}`} />
                  {section.titleFil} / {section.title}
                </span>
                <Badge
                  variant={allDone ? "default" : "outline"}
                  className="text-xs"
                >
                  {doneCount}/{totalItems}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {section.items.map((item, i) => {
                const key = `${section.id}-${i}`;
                const isDone = !!checked[key];
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggle(key)}
                    className={`flex items-start gap-3 w-full text-left p-3 rounded-lg border transition-all ${
                      isDone
                        ? "bg-primary/5 border-primary/20"
                        : "border-border/50 hover:bg-accent/50"
                    }`}
                  >
                    <CheckCircle
                      className={`h-5 w-5 mt-0.5 shrink-0 transition-colors ${
                        isDone ? "text-primary" : "text-muted-foreground/30"
                      }`}
                    />
                    <div className="flex-1">
                      <p
                        className={`text-sm ${
                          isDone
                            ? "line-through text-muted-foreground"
                            : "text-foreground"
                        }`}
                      >
                        {item.en}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {item.fil}
                      </p>
                    </div>
                  </button>
                );
              })}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
