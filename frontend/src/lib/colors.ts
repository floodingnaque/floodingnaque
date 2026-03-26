/**
 * Centralized risk color constants - single source of truth.
 *
 * Tailwind classes reference CSS custom properties (--risk-safe, etc.).
 * This module provides the **computed hex values** needed by chart libraries,
 * SVG inline styles, and Leaflet map markers that cannot read CSS vars.
 *
 * Keep in sync with `src/index.css` `:root` / `.dark` definitions.
 */

/** Hex risk colors matching the light-mode CSS variables. */
export const RISK_HEX = {
  safe: "#28A745",
  alert: "#FFC107",
  critical: "#DC3545",
  unknown: "#6b7280",
} as const;

/**
 * WCAG AA-compliant text colors for use on top of the risk backgrounds.
 * Alert yellow (#FFC107) only achieves 1.3:1 with white text.
 * Dark brown (#713f12) on yellow gives 7.1:1 - well above the AA minimum.
 */
export const RISK_TEXT_HEX = {
  safe: "#ffffff",
  alert: "#713f12",
  critical: "#ffffff",
  unknown: "#ffffff",
} as const;

/** Semi-transparent fill colors for map overlays. */
export const RISK_FILL_HEX = {
  safe: "rgba(40,167,69,0.18)",
  alert: "rgba(255,193,7,0.22)",
  critical: "rgba(220,53,69,0.28)",
  unknown: "rgba(107,114,128,0.15)",
} as const;

/** Primary brand color hex (--primary light mode). */
export const PRIMARY_HEX = "#1E3A5F";

/**
 * Read a CSS custom property as an `hsl(...)` string at runtime.
 * Falls back to the provided default if the variable is unset.
 */
export function cssVar(name: string, fallback?: string): string {
  if (typeof document === "undefined") return fallback ?? "";
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return raw ? `hsl(${raw})` : (fallback ?? "");
}
