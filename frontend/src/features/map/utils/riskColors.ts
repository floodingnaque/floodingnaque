/**
 * Risk colour palette utilities for map overlays.
 *
 * Extracted from HazardOverlay to satisfy react-refresh/only-export-components.
 * Uses the centralized color constants from @/lib/colors.
 */

import { RISK_FILL_HEX, RISK_HEX } from "@/lib/colors";

/** Stroke colours for each risk classification. */
export const RISK_COLORS: Record<string, string> = {
  safe: RISK_HEX.safe,
  alert: RISK_HEX.alert,
  critical: RISK_HEX.critical,
  unknown: RISK_HEX.unknown,
};

/** Semi-transparent fill colours for each risk classification. */
export const RISK_FILL_COLORS: Record<string, string> = {
  safe: RISK_FILL_HEX.safe,
  alert: RISK_FILL_HEX.alert,
  critical: RISK_FILL_HEX.critical,
  unknown: RISK_FILL_HEX.unknown,
};

/** Return PathOptions overrides for a given risk level string. */
export function getRiskLevelStyle(risk: string): {
  color: string;
  fillColor: string;
} {
  const key = risk.toLowerCase();
  return {
    color: RISK_COLORS[key] ?? RISK_COLORS.unknown ?? "#6c757d",
    fillColor: RISK_FILL_COLORS[key] ?? RISK_FILL_COLORS.unknown ?? "#6c757d80",
  };
}
