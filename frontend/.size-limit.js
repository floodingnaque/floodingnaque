/**
 * size-limit configuration for Floodingnaque frontend.
 * Run: npm run size        (show current sizes)
 *      npm run size:check  (fail if over budget)
 *
 * Budget rationale:
 * - JS total ~500KB: React 19 + Radix UI + TanStack Query + Recharts + Leaflet
 * - CSS ~50KB: Tailwind purged output
 * - Main chunk kept small for initial page load; heavy libs lazy-loaded via routes
 */
module.exports = [
  {
    name: "JS total",
    path: "dist/assets/*.js",
    limit: "500 KB",
  },
  {
    name: "CSS total",
    path: "dist/assets/*.css",
    limit: "50 KB",
  },
  {
    name: "Entry point (index.html + initial JS)",
    path: "dist/index.html",
    limit: "15 KB",
  },
];
