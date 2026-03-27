/**
 * MapLayerControl Component
 *
 * Floating glass-effect panel overlaid on the Leaflet map that lets
 * users toggle GIS overlay layers and switch between base-map styles.
 *
 * Layers:
 *  - Barangay Boundaries (blue)
 *  - Flood Risk Zones (red)
 *  - Evacuation Centers (green)
 *  - Road Network (amber)
 *
 * Base maps:
 *  - Standard (OpenStreetMap)
 *  - Satellite (Esri World Imagery)
 *  - Topographic (OpenTopoMap)
 */

import { cn } from "@/lib/cn";
import {
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Layers,
  Map,
  Mountain,
  Satellite,
} from "lucide-react";
import { useCallback, useState } from "react";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type BaseMapType = "standard" | "satellite" | "topo";

export interface LayerVisibility {
  boundaries: boolean;
  floodZones: boolean;
  evacuation: boolean;
  traffic: boolean;
  communityReports: boolean;
  safeRoute: boolean;
  floodDepth: boolean;
}

export interface MapLayerControlProps {
  layers: LayerVisibility;
  onLayerChange: (layers: LayerVisibility) => void;
  baseMap: BaseMapType;
  onBaseMapChange: (baseMap: BaseMapType) => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Option descriptors
// ---------------------------------------------------------------------------

const BASE_MAP_OPTIONS: {
  value: BaseMapType;
  label: string;
  icon: React.ReactNode;
}[] = [
  { value: "standard", label: "Standard", icon: <Map className="h-4 w-4" /> },
  {
    value: "satellite",
    label: "Satellite",
    icon: <Satellite className="h-4 w-4" />,
  },
  { value: "topo", label: "Topo", icon: <Mountain className="h-4 w-4" /> },
];

const LAYER_OPTIONS: {
  key: keyof LayerVisibility;
  label: string;
  color: string;
  activeColor: string;
}[] = [
  {
    key: "boundaries",
    label: "Barangay Boundaries",
    color: "border-blue-400",
    activeColor: "bg-blue-500 border-blue-500",
  },
  {
    key: "floodZones",
    label: "Flood Risk Zones",
    color: "border-risk-critical",
    activeColor: "bg-risk-critical border-risk-critical",
  },
  {
    key: "evacuation",
    label: "Evacuation Centers",
    color: "border-risk-safe",
    activeColor: "bg-risk-safe border-risk-safe",
  },
  {
    key: "traffic",
    label: "Road Network",
    color: "border-risk-alert",
    activeColor: "bg-risk-alert border-risk-alert",
  },
  {
    key: "communityReports",
    label: "Community Reports",
    color: "border-cyan-400",
    activeColor: "bg-cyan-500 border-cyan-500",
  },
  {
    key: "safeRoute",
    label: "Safe Route",
    color: "border-indigo-400",
    activeColor: "bg-indigo-500 border-indigo-500",
  },
  {
    key: "floodDepth",
    label: "Flood Depth",
    color: "border-blue-600",
    activeColor: "bg-blue-700 border-blue-700",
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MapLayerControl({
  layers,
  onLayerChange,
  baseMap,
  onBaseMapChange,
  className,
}: MapLayerControlProps) {
  const [collapsed, setCollapsed] = useState(true);

  const toggleLayer = useCallback(
    (key: keyof LayerVisibility) => {
      onLayerChange({ ...layers, [key]: !layers[key] });
    },
    [layers, onLayerChange],
  );

  const activeCount = Object.values(layers).filter(Boolean).length;

  return (
    <div
      className={cn(
        "absolute top-3 right-3 z-500 w-56",
        "rounded-xl bg-white/90 dark:bg-gray-900/90 backdrop-blur-md",
        "border border-gray-200/80 dark:border-gray-700/80 shadow-xl",
        "text-sm select-none transition-all duration-200",
        className,
      )}
    >
      {/* --- Header ---- */}
      <button
        className={cn(
          "flex w-full items-center justify-between px-3 py-2.5",
          "font-semibold text-gray-700 dark:text-gray-200",
          "hover:bg-gray-50/80 dark:hover:bg-gray-800/60 transition-colors",
          collapsed ? "rounded-xl" : "rounded-t-xl",
        )}
        onClick={() => setCollapsed((c) => !c)}
        aria-expanded={!collapsed}
        aria-label="Toggle layer control panel"
      >
        <span className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <span>Map Layers</span>
          <span className="ml-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
            {activeCount}
          </span>
        </span>
        {collapsed ? (
          <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
        ) : (
          <ChevronUp className="h-3.5 w-3.5 text-gray-400" />
        )}
      </button>

      {!collapsed && (
        <div className="px-3 pb-3 space-y-3 border-t border-gray-100 dark:border-gray-800 pt-2.5">
          {/* ---- Base Map ---- */}
          <div>
            <p className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1.5 font-bold">
              <Map className="h-3 w-3" />
              Base Map
            </p>
            <div className="grid grid-cols-3 gap-1">
              {BASE_MAP_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={cn(
                    "flex flex-col items-center gap-0.5 rounded-lg px-1.5 py-1.5 text-[11px] font-medium transition-all",
                    baseMap === opt.value
                      ? "bg-primary text-primary-foreground shadow-sm ring-1 ring-primary/30"
                      : "bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700",
                  )}
                  onClick={() => onBaseMapChange(opt.value)}
                >
                  <span className="text-sm leading-none">{opt.icon}</span>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* ---- Layer Toggles ---- */}
          <div>
            <p className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1.5 font-bold">
              <Eye className="h-3 w-3" />
              Overlays
            </p>
            <div className="space-y-1">
              {LAYER_OPTIONS.map((opt) => {
                const isActive = layers[opt.key];
                return (
                  <button
                    key={opt.key}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 transition-all",
                      "hover:bg-gray-50 dark:hover:bg-gray-800/60",
                      isActive && "bg-gray-50/80 dark:bg-gray-800/40",
                    )}
                    onClick={() => toggleLayer(opt.key)}
                    role="switch"
                    aria-checked={isActive}
                  >
                    {/* Checkbox indicator */}
                    <span
                      className={cn(
                        "flex h-4 w-4 shrink-0 items-center justify-center rounded border-2 transition-colors",
                        isActive ? opt.activeColor : opt.color,
                      )}
                    >
                      {isActive && (
                        <svg
                          className="h-2.5 w-2.5 text-white"
                          viewBox="0 0 12 12"
                          fill="none"
                        >
                          <path
                            d="M2.5 6l2.5 2.5 4.5-5"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </span>

                    {/* Label */}
                    <span
                      className={cn(
                        "flex-1 text-left text-xs transition-colors",
                        isActive
                          ? "text-gray-800 dark:text-gray-100 font-medium"
                          : "text-gray-500 dark:text-gray-400",
                      )}
                    >
                      {opt.label}
                    </span>

                    {/* Eye icon */}
                    {isActive ? (
                      <Eye className="h-3 w-3 text-gray-400" />
                    ) : (
                      <EyeOff className="h-3 w-3 text-gray-300 dark:text-gray-600" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MapLayerControl;
